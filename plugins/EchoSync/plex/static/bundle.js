//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function v(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function ne() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var y = 1024, b = 2048, x = 4096, S = 8192, re = 16384, ie = 32768, ae = 1 << 25, oe = 65536, se = 1 << 19, ce = 1 << 20, le = 65536, ue = 1 << 21, de = 1 << 22, fe = 1 << 23, pe = Symbol("$state"), me = Symbol("legacy props"), he = Symbol(""), ge = Symbol("attributes"), _e = Symbol("class"), ve = Symbol("style"), ye = Symbol("text"), be = Symbol("form reset"), xe = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), Se = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Ce(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function we() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Te(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ee() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function De(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Oe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ke() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ae(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function je() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Pe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Fe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ie(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Le() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var C = !1;
function Re(e) {
	C = e;
}
var w;
function T(e) {
	if (e === null) throw Ie(), r;
	return w = e;
}
function ze() {
	return T(/* @__PURE__ */ F(w));
}
function E(e) {
	if (C) {
		if (/* @__PURE__ */ F(w) !== null) throw Ie(), r;
		w = e;
	}
}
function Be(e = 1) {
	if (C) {
		for (var t = e, n = w; t--;) n = /* @__PURE__ */ F(n);
		w = n;
	}
}
function Ve(e = !0) {
	for (var t = 0, n = w;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ F(n);
		e && n.remove(), n = i;
	}
}
function He(e) {
	if (!e || e.nodeType !== 8) throw Ie(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ue(e) {
	return e === this.v;
}
function We(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ge(e) {
	return !We(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var D = null;
function Ke(e) {
	D = e;
}
function qe(e, n = !1, r) {
	D = {
		p: D,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = D, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) xn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, D = t.p, e ?? {};
}
function Ye() {
	return !t || D !== null && D.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], v(e);
}
function Qe(e) {
	if (Xe.length === 0 && !At) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function $e() {
	for (; Xe.length > 0;) Ze();
}
function et(e) {
	var t = G;
	if (t === null) return H.f |= fe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	tt(e, t);
}
function tt(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var nt = ~(b | x | y);
function O(e, t) {
	e.f = e.f & nt | t;
}
function rt(e) {
	e.f & 512 || e.deps === null ? O(e, y) : O(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function it(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= le, it(t.deps));
}
function at(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), it(e.deps), O(e, y);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var ot = !1, st = !1;
function ct(e) {
	var t = st;
	try {
		return st = !1, [e(), st];
	} finally {
		st = t;
	}
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function lt(e) {
	let t = 0, n = Jt(0), r;
	return () => {
		vn() && (Z(n), Dn(() => (t === 0 && (r = ar(() => e(() => Zt(n)))), t += 1, () => {
			Qe(() => {
				--t, t === 0 && (r?.(), r = void 0, Zt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ut = oe | se;
function dt(e, t, n, r) {
	new ft(e, t, n, r);
}
var ft = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = C ? w : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = lt(() => (this.#m = Jt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = kn(() => {
			if (C) {
				let e = this.#t;
				ze();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, ut), C && (this.#e = w);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = on();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Fn(this.#o, () => {
				this.#o = null;
			}), this.#b(k));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				zn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(k);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		at(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = D;
		K(this.#i), W(this.#i), Ke(this.#i.ctx);
		try {
			return It.ensure(), e();
		} catch (e) {
			return et(e), null;
		} finally {
			K(t), W(n), Ke(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Fn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Qe(() => {
			this.#d = !1, this.#m && Yt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), C && (T(this.#t), Be(), T(Ve()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Le();
				return;
			}
			r = !0, i && Pe(), this.#s !== null && Fn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return tt(e, this.#i.parent), null;
				}
			}));
		};
		Qe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => tt(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function pt(e, t, n, r) {
	let i = Ye() ? _t : bt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = mt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				tt(e, s);
			}
			ht();
		}
	}
	var d = gt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ yt(e))).then(u).catch((e) => tt(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), ht();
	}) : f();
}
function mt() {
	var e = G, t = H, n = D, r = k;
	return function(i = !0) {
		K(e), W(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function ht(e = !0) {
	K(null), W(null), Ke(null), e && k?.deactivate();
}
function gt() {
	var e = G, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function _t(e) {
	var t = 2 | b;
	return G !== null && (G.f |= se), {
		ctx: D,
		deps: null,
		effects: null,
		equals: Ue,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
var vt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function yt(e, t, n) {
	let r = G;
	r === null && we();
	var a = void 0, o = Jt(i), s = !H, c = /* @__PURE__ */ new Set();
	return En(() => {
		var t = G, n = ne();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== xe && n.reject(e);
			}).finally(ht);
		} catch (e) {
			n.reject(e), ht();
		}
		var i = k;
		if (s) {
			if (t.f & 32768) var l = gt();
			if (r.b?.is_rendered()) i.async_deriveds.get(t)?.reject(vt);
			else for (let e of c.values()) e.reject(vt);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== vt && (i.activate(), t ? (o.f |= fe, Yt(o, t)) : (o.f & 8388608 && (o.f ^= fe), Yt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), yn(() => {
		for (let e of c) e.reject(vt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function bt(e) {
	let t = /* @__PURE__ */ _t(e);
	return t.equals = Ge, t;
}
function xt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function St(e) {
	var t, n = G, r = e.parent;
	if (!V && r !== null && e.v !== i && r.f & 24576) return Fe(), e.v;
	K(r);
	try {
		e.f &= ~le, xt(e), t = Qn(e);
	} finally {
		K(n);
	}
	return t;
}
function Ct(e) {
	var t = St(e);
	if (!e.equals(t) && (e.wv = Yn(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), Ot?.capture(e, t, !0)), e.deps === null))) {
		O(e, y);
		return;
	}
	V || (A === null ? rt(e) : (vn() || k?.is_fork) && A.set(e, t));
}
function wt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(xe), t.fn !== null && (t.teardown = ee), t.ac = null, er(t, 0), jn(t));
}
function Tt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && tr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Et = null, Dt = null, k = null, Ot = null, A = null, kt = null, At = !1, jt = !1, Mt = null, Nt = null, Pt = 0, Ft = 1, It = class t {
	id = Ft++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		Dt === null ? Et = Dt = this : (Dt.#n = this, this.#t = Dt), Dt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) O(r, b), t(r);
			for (r of n.m) O(r, x), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, Pt++ > 1e3 && (this.#S(), Rt());
		for (let e of this.#u) this.#d.delete(e), O(e, b), this.schedule(e);
		for (let e of this.#d) O(e, x), this.schedule(e);
		let n = this.#c;
		this.#c = [], this.apply();
		var r = Mt = [], i = [], a = Nt = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw Wt(e), this.#h() || this.discard(), t;
		}
		if (k = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (Mt = null, Nt = null, this.#h()) {
			this.#b(i), this.#b(r);
			for (let [e, t] of this.#f) Ut(e, t);
			a.length > 0 && k.#g();
			return;
		}
		let s = this.#v();
		if (s) {
			this.#b(i), this.#b(r), s.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), Ot = this, zt(i), zt(r), Ot = null, this.#s?.resolve();
		var c = k;
		if (this.#a === 0 && (this.#c.length === 0 || c !== null) && (this.#S(), e && (this.#x(), k = c)), this.#c.length > 0) if (c !== null) {
			let e = c;
			e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
		} else c = this;
		c !== null && c.#g();
	}
	#_(t, n, r) {
		t.f ^= y;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#f.has(i)) && i.fn !== null) {
				o ? i.f ^= y : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Xn(i) && (a & 16 && this.#d.add(i), tr(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), O(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#S(), k = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) at(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), A?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		k = this;
	}
	deactivate() {
		k = null, A = null;
	}
	flush() {
		try {
			jt = !0, k = this, this.#g();
		} finally {
			Pt = 0, kt = null, Mt = null, Nt = null, jt = !1, k = null, A = null, Kt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(vt);
		this.#S(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	#x() {
		for (let u = Et; u !== null; u = u.#n) {
			var e = u.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (u.current.has(r)) {
					var n = u.current.get(r)[0];
					if (e && i !== n) u.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = u.async_deriveds.get(e);
				n && t.promise.then(n.resolve).catch(n.reject);
			}
			var r = [...u.current.keys()].filter((e) => !u.current.get(e)[1]);
			if (!(!u.#e || r.length === 0)) {
				var i = r.filter((e) => !this.current.has(e));
				if (i.length === 0) e && u.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#p) u.unskip_effect(e, (e) => {
						e.f & 4194320 ? u.schedule(e) : u.#b([e]);
					});
					u.activate();
					var a = /* @__PURE__ */ new Set(), o = /* @__PURE__ */ new Map();
					for (var s of t) Bt(s, i, a, o);
					o = /* @__PURE__ */ new Map();
					var c = [...u.current].filter(([e, t]) => {
						let n = this.current.get(e);
						return n ? n[0] !== t[0] || n[1] !== t[1] : !0;
					}).map(([e]) => e);
					if (c.length > 0) for (let e of this.#l) !(e.f & 155648) && Vt(e, c, o) && (e.f & 4194320 ? (O(e, b), u.schedule(e)) : u.#u.add(e));
					if (u.#c.length > 0 && !u.#m) {
						u.apply();
						for (var l of u.#c) u.#_(l, [], []);
						u.#c = [];
					}
					u.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Qe(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= ne()).promise;
	}
	static ensure() {
		if (k === null) {
			let e = k = new t();
			!jt && !At && Qe(() => {
				e.#e || e.flush();
			});
		}
		return k;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			A = null;
			return;
		}
		A = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) A.set(e, t);
		for (let e = Et; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) A.has(t) || A.set(t, n);
		}
	}
	schedule(t) {
		if (kt = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (Mt !== null && n === G && (e || (H === null || !(H.f & 2)) && !ot)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= y;
			}
		}
		this.#c.push(n);
	}
	#S() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null ? Et = t : e.#n = t, t === null ? Dt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Lt(e) {
	var t = At;
	At = !0;
	try {
		var n;
		for (e && (k !== null && !k.is_fork && k.flush(), n = e());;) {
			if ($e(), k === null) return n;
			k.flush();
		}
	} finally {
		At = t;
	}
}
function Rt() {
	try {
		Oe();
	} catch (e) {
		tt(e, kt);
	}
}
var j = null;
function zt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Xn(r) && (j = /* @__PURE__ */ new Set(), tr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Pn(r), j?.size > 0)) {
				Kt.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || tr(n);
					}
				}
				j.clear();
			}
		}
		j = null;
	}
}
function Bt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? Bt(i, t, n, r) : e & 4194320 && !(e & 2048) && Vt(i, t, r) && (O(i, b), Ht(i));
	}
}
function Vt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && Vt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Ht(e) {
	k.schedule(e);
}
function Ut(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, y);
		for (var n = e.first; n !== null;) Ut(n, t), n = n.next;
	}
}
function Wt(e) {
	O(e, y);
	for (var t = e.first; t !== null;) Wt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Gt = /* @__PURE__ */ new Set(), Kt = /* @__PURE__ */ new Map(), qt = !1;
function Jt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ue,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function M(e, t) {
	let n = Jt(e, t);
	return Un(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(e, n = !1, r = !0) {
	let i = Jt(e);
	return n || (i.equals = Ge), t && r && D !== null && D.l !== null && (D.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Ye() && H.f & 4325394 && (q === null || !q.has(e)) && Ne(), Yt(e, n ? $t(t) : t, Nt);
}
function Yt(e, t, n = null) {
	if (!e.equals(t)) {
		Kt.set(e, V ? t : e.v);
		var r = It.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && St(t), A === null && rt(t);
		}
		e.wv = Yn(), Qt(e, b, n), Ye() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Wn([e]) : X.push(e)), !r.is_fork && Gt.size > 0 && !qt && Xt();
	}
	return t;
}
function Xt() {
	qt = !1;
	for (let e of Gt) {
		e.f & 1024 && O(e, x);
		let t;
		try {
			t = Xn(e);
		} catch {
			t = !0;
		}
		t && tr(e);
	}
	Gt.clear();
}
function Zt(e) {
	P(e, e.v + 1);
}
function Qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & b) === 0;
			if (l && O(s, t), c & 131072) Gt.add(s);
			else if (c & 2) {
				var u = s;
				A?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= le), Qt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && j !== null && j.add(d), n === null ? Ht(d) : n.push(d);
			}
		}
	}
}
function $t(e) {
	if (typeof e != "object" || !e || pe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ M(0), s = null, c = qn, l = (e) => {
		if (qn === c) return e();
		var t = H, n = qn;
		W(null), Jn(c);
		var r = e();
		return W(t), Jn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ M(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ M(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ M(i, s));
					n.set(t, e), Zt(a);
				}
			} else P(r, i), Zt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === pe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ M($t(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Z(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Z(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === pe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ M(a ? $t(e[t]) : i, s)), n.set(t, r)), Z(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ M(i, s)), n.set(p + "", m)) : P(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ M(void 0, s)), P(u, $t(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => $t(o));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && P(_, ee + 1);
				}
				Zt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Z(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Me();
		}
	});
}
var en, tn, nn, rn;
function an() {
	if (en === void 0) {
		en = window, tn = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		nn = f(t, "firstChild").get, rn = f(t, "nextSibling").get, _(e) && (e[_e] = void 0, e[ge] = null, e[ve] = void 0, e.__e = void 0), _(n) && (n[ye] = void 0);
	}
}
function on(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function sn(e) {
	return nn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function F(e) {
	return rn.call(e);
}
function I(e, t) {
	if (!C) return /* @__PURE__ */ sn(e);
	var n = /* @__PURE__ */ sn(w);
	if (n === null) n = w.appendChild(on());
	else if (t && n.nodeType !== 3) {
		var r = on();
		return n?.before(r), T(r), r;
	}
	return t && dn(n), T(n), n;
}
function L(e, t = 1, n = !1) {
	let r = C ? w : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ F(r);
	if (!C) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = on();
			return r === null ? i?.after(a) : r.before(a), T(a), a;
		}
		dn(r);
	}
	return T(r), r;
}
function cn(e) {
	e.textContent = "";
}
function ln() {
	return !e || j !== null ? !1 : (G.f & ie) !== 0;
}
function un(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function dn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var fn = !1;
function pn() {
	fn || (fn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[be]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function mn(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function hn(e, t, n, r = n) {
	e.addEventListener(t, () => mn(n));
	let i = e[be];
	i ? e[be] = () => {
		i(), r(!0);
	} : e[be] = () => r(!0), pn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function gn(e) {
	G === null && (H === null && De(e), Ee()), V && Te(e);
}
function _n(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= S);
	var r = {
		ctx: D,
		deps: null,
		nodes: null,
		f: e | b | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	k?.register_created_effect(r);
	var i = r;
	if (e & 4) Mt === null ? It.ensure().schedule(r) : Mt.push(r);
	else if (t !== null) {
		try {
			tr(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= oe));
	}
	if (i !== null && (i.parent = n, n !== null && _n(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function vn() {
	return H !== null && !U;
}
function yn(e) {
	let t = R(8, null);
	return O(t, y), t.teardown = e, t;
}
function bn(e) {
	gn("$effect");
	var t = G.f;
	if (!H && t & 32 && D !== null && !D.i) {
		var n = D;
		(n.e ??= []).push(e);
	} else return xn(e);
}
function xn(e) {
	return R(4 | ce, e);
}
function Sn(e) {
	return gn("$effect.pre"), R(8 | ce, e);
}
function Cn(e) {
	It.ensure();
	let t = R(64 | se, e);
	return () => {
		B(t);
	};
}
function wn(e) {
	It.ensure();
	let t = R(64 | se, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Fn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Tn(e) {
	return R(4, e);
}
function En(e) {
	return R(de | se, e);
}
function Dn(e, t = 0) {
	return R(8 | t, e);
}
function On(e, t = [], n = [], r = []) {
	pt(r, t, n, (t) => {
		R(8, () => {
			e(...t.map(Z));
		});
	});
}
function kn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | se, e);
}
function An(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		Hn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Hn(e), W(n);
		}
	}
}
function jn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && mn(() => {
			e.abort(xe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Mn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Nn(e.nodes.start, e.nodes.end), n = !0), e.f |= ae, jn(e, t && !n), er(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	An(e), e.f ^= ae, e.f |= re;
	var i = e.parent;
	i !== null && i.first !== null && Pn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Nn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ F(e);
		e.remove(), e = n;
	}
}
function Pn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Fn(e, t, n = !0) {
	var r = [];
	In(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function In(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= S;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				In(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Ln(e) {
	Rn(e, !0);
}
function Rn(e, t) {
	if (e.f & 8192) {
		e.f ^= S, e.f & 1024 || (O(e, b), It.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Rn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function zn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ F(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Bn = null, Vn = !1, V = !1;
function Hn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Un(t) {
	H !== null && (!e || H.f & 2) && (q ??= /* @__PURE__ */ new Set()).add(t);
}
var J = null, Y = 0, X = null;
function Wn(e) {
	X = e;
}
var Gn = 1, Kn = 0, qn = Kn;
function Jn(e) {
	qn = e;
}
function Yn() {
	return ++Gn;
}
function Xn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~le), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Xn(a) && Ct(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, y);
	}
	return !1;
}
function Zn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && q !== null && q.has(t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Zn(o, n, !1) : n === o && (r ? O(o, b) : o.f & 1024 && O(o, x), Ht(o));
	}
}
function Qn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = D, s = U, c = qn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ke(e.ctx), U = !1, qn = ++Kn, e.ac !== null && (mn(() => {
		e.ac.abort(xe);
	}), e.ac = null);
	try {
		e.f |= ue;
		var u = e.fn, d = u();
		e.f |= ie;
		var f = e.deps, p = k?.is_fork;
		if (J !== null) {
			var m;
			if (p || er(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (vn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (er(e, Y), f.length = Y);
		if (Ye() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Zn(X[m], e);
		if (i !== null && i !== e) {
			if (Kn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Kn;
			if (t !== null) for (let e of t) e.rv = Kn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= fe), d;
	} catch (e) {
		return et(e);
	} finally {
		e.f ^= ue, J = t, Y = n, X = r, H = i, q = a, Ke(o), U = s, qn = c;
	}
}
function $n(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !c.call(J, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~le), o.v !== i && rt(o), wt(o), er(o, 0);
	}
}
function er(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) $n(e, n[r]);
}
function tr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, y);
		var n = G, r = Vn;
		G = e, Vn = !0;
		try {
			t & 16777232 ? Mn(e) : jn(e), An(e);
			var i = Qn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Gn;
		} finally {
			Vn = r, G = n;
		}
	}
}
async function nr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), Lt();
}
function Z(e) {
	var t = (e.f & 2) != 0;
	if (Bn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Kn && (e.rv = Kn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], c.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (V && Kt.has(e)) return Kt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || ir(i)) && (a = St(i)), Kt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Vn || (H.f & 512) != 0), s = (i.f & ie) === 0;
		Xn(i) && (o && (i.f |= 512), Ct(i)), o && !s && (Tt(i), rr(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function rr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Tt(t), rr(t));
}
function ir(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Kt.has(t) || t.f & 2 && ir(t)) return !0;
	return !1;
}
function ar(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function or(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (pe in e) sr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && pe in n && sr(n);
		}
	}
}
function sr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			sr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var cr = Symbol("events"), lr = /* @__PURE__ */ new Set(), ur = /* @__PURE__ */ new Set();
function dr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || mr.call(t, e), !e.cancelBubble) return mn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function fr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = dr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && yn(() => {
		t.removeEventListener(e, o, a);
	});
}
var pr = null;
function mr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	pr = e;
	var o = 0, s = pr === e && e[cr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[cr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[cr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[cr] = t, delete e.currentTarget, W(u), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var hr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function gr(e) {
	return hr?.createHTML(e) ?? e;
}
function _r(e) {
	var t = un("template");
	return t.innerHTML = gr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function vr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (C) return vr(w, null), w;
		i === void 0 && (i = _r(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ sn(i)));
		var t = r || tn ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ sn(t), s = t.lastChild;
			vr(o, s);
		} else vr(t, t);
		return t;
	};
}
function $(e, t) {
	if (C) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = w), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var yr = ["touchstart", "touchmove"];
function br(e) {
	return yr.includes(e);
}
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ye] ??= e.nodeValue) && (e[ye] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	an(), t.intro = t.intro ?? !1;
	let n = t.target, i = C, a = w;
	try {
		for (var o = /* @__PURE__ */ sn(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ F(o);
		if (!o) throw r;
		Re(!0), T(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), an(), cn(n), Re(!1), Sr(e, t);
	} finally {
		Re(i), T(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	an();
	var u = void 0, d = wn(() => {
		var s = n ?? t.appendChild(on());
		dt(s, { pending: () => {} }, (t) => {
			qe({});
			var n = D;
			if (o && (n.c = o), a && (i.$$events = a), C && vr(t, null), u = e(t, i) || {}, C && (G.nodes.end = w, w === null || w.nodeType !== 8 || w.data !== "]")) throw Ie(), r;
			Je();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = br(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, mr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(lr)), ur.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = wr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, mr), r.delete(e), r.size === 0 && wr.delete(n)) : r.set(e, i);
			}
			ur.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Ln(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Ln(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						zn(r, t), t.append(on()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Fn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = ln();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = on();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else C && (this.anchor = w), this.#a(n);
	}
};
function kr(e) {
	D === null && Ce("onMount"), t && D.l !== null ? Ar(D).m.push(e) : bn(() => {
		let t = ar(e);
		if (typeof t == "function") return t;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	C && (r = w, ze());
	var i = new Or(e), a = n ? oe : 0;
	function o(e, t) {
		if (C) {
			var n = He(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ve();
				T(a), i.anchor = a, Re(!1), i.ensure(e, t), Re(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	kn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Mr(e, t) {
	Tn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = un("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Nr = Symbol("is custom element"), Pr = Symbol("is html"), Fr = Se ? "link" : "LINK";
function Ir(e) {
	if (C) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Lr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Lr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[be] = n, Qe(n), pn();
	}
}
function Lr(e, t, n, r) {
	var i = Rr(e);
	C && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Fr) || i[t] !== (i[t] = n) && (t === "loading" && (e[he] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Br(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Rr(e) {
	return e[ge] ??= {
		[Nr]: e.nodeName.includes("-"),
		[Pr]: e.namespaceURI === a
	};
}
var zr = /* @__PURE__ */ new Map();
function Br(e) {
	var t = e.getAttribute("is") || e.nodeName, n = zr.get(t);
	if (n) return n;
	zr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Vr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	hn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Hr(t) ? Ur(a) : a, r(a), k !== null && i.add(k), await nr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (C && t.defaultValue !== t.value || ar(n) == null && t.value) && (r(Hr(t) ? Ur(t.value) : t.value), k !== null && i.add(k)), Dn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? Ot : k;
			if (i.has(a)) return;
		}
		Hr(t) && r === Ur(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Hr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Ur(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Wr(e = !1) {
	let t = D, n = t.l.u;
	if (!n) return;
	let r = () => or(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ _t(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && Sn(() => {
		Gr(t, r), v(n.b);
	}), bn(() => {
		let e = ar(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && bn(() => {
		Gr(t, r), v(n.a);
	});
}
function Gr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Kr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ _t(i), Z(u)) : (l && (l = !1, c = s ? ar(i) : i), c);
	let p;
	if (o) {
		var m = pe in e || me in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ct(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && Ae(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var ee = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || ee || g) && p(t ? _() : e), e) : _();
		});
	}
	var te = !1, v = (r & 1 ? _t : bt)(() => (te = !1, _()));
	o && Z(v);
	var ne = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(v) : a && o ? $t(e) : e;
			return P(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return V && te || ne.f & 16384 ? v.v : Z(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function qr(e) {
	return new Jr(e);
}
var Jr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ N(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Z(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === me ? !0 : (Z(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return P(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Cr : Sr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && Lt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Yr;
typeof HTMLElement == "function" && (Yr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = un("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Zr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Xr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = qr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Cn(() => {
				Dn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Xr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Xr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Xr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Zr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Qr(e, t, n, r, i, a) {
	let o = class extends Yr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Xr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region PlexCard.svelte
var $r = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-lueg2f\">Active</span>"), ei = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Authenticated</span>"), ti = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Connected</span>"), ni = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-lueg2f\">Disconnected</span>"), ri = /* @__PURE__ */ Q("<div class=\"loading-state svelte-lueg2f\"><div class=\"spinner svelte-lueg2f\"></div> <span>Linking with Plex Nexus...</span></div>"), ii = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\"> </button>"), ai = /* @__PURE__ */ Q("<button class=\"btn-ghost accent svelte-lueg2f\"> </button>"), oi = /* @__PURE__ */ Q("<button class=\"btn-danger-ghost svelte-lueg2f\">Cancel Authorization</button>"), si = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\">Switch Account</button>"), ci = /* @__PURE__ */ Q("<button class=\"btn-primary plex-btn svelte-lueg2f\"><svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z\"></path></svg> Sign in with Plex</button>"), li = /* @__PURE__ */ Q("<div class=\"settings-section svelte-lueg2f\"><div class=\"form-grid svelte-lueg2f\"><div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Server Access URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input-field svelte-lueg2f\"/> <span class=\"helper-text svelte-lueg2f\">Typically http://[IP]:32400. Use localhost if running natively.</span></div> <div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Friendly Name</span> <input type=\"text\" placeholder=\"e.g. Home Media\" class=\"input-field svelte-lueg2f\"/></div> <div class=\"actions-row svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <div class=\"auth-box svelte-lueg2f\"><!></div></div></div></div>"), ui = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"card-title svelte-lueg2f\">Plex Media Server</h2> <div class=\"badges svelte-lueg2f\"><!> <!> <!></div></div> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <!></section>"), di = {
	hash: "svelte-lueg2f",
	code: "\n  /* SHADOW DOM STYLING */.plugin-card.svelte-lueg2f {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;color:var(--text-primary);font-family:inherit;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:16px;}.card-title.svelte-lueg2f {margin:0;font-size:18px;font-weight:700;letter-spacing:-0.01em;}.badges.svelte-lueg2f {display:flex;gap:8px;}.status-badge.svelte-lueg2f {font-size:9px;padding:2px 8px;border-radius:5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;}.status-badge.active.svelte-lueg2f {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-lueg2f {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-lueg2f {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-lueg2f,\n  .btn-ghost-small.svelte-lueg2f,\n  .btn-danger-ghost.svelte-lueg2f {padding:10px 18px;background:rgba(255, 255, 255, 0.04);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-ghost-small.svelte-lueg2f {padding:6px 12px;font-size:11px;border-radius:6px;}.btn-ghost.svelte-lueg2f:hover,\n  .btn-ghost-small.svelte-lueg2f:hover {background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.2);}.btn-ghost.accent.svelte-lueg2f {color:var(--color-primary);border-color:rgba(20, 184, 166, 0.3);}.btn-danger-ghost.svelte-lueg2f {color:#ef4444;border-color:rgba(239, 68, 68, 0.2);}.btn-primary.svelte-lueg2f {padding:10px 24px;background:var(--color-primary);color:#000;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-1px);}.plex-btn.svelte-lueg2f {display:flex;align-items:center;gap:8px;background:#e5a00d; /* Plex Gold */color:#000;}.loading-state.svelte-lueg2f {display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);}.spinner.svelte-lueg2f {width:28px;height:28px;border:3px solid rgba(255, 255, 255, 0.05);border-top-color:var(--color-primary);border-radius:50%;\n    animation: svelte-lueg2f-spin 1s linear infinite;}\n\n  @keyframes svelte-lueg2f-spin {\n    to {\n      transform: rotate(360deg);\n    }\n  }.settings-section.svelte-lueg2f {margin-top:8px;}.form-grid.svelte-lueg2f {display:flex;flex-direction:column;gap:20px;}.form-field.svelte-lueg2f {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-lueg2f {font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;}.input-field.svelte-lueg2f {width:100%;padding:12px 16px;background:var(--bg-input, #0b0f1a);border:1px solid var(--border-subtle);border-radius:10px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-lueg2f:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 3px rgba(20, 184, 166, 0.1);}.helper-text.svelte-lueg2f {font-size:11px;color:var(--text-muted);font-style:italic;}.actions-row.svelte-lueg2f {display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px;}.auth-box.svelte-lueg2f {margin-left:auto;}\n\n  @media (max-width: 600px) {.auth-box.svelte-lueg2f {margin-left:0;width:100%;}.auth-box.svelte-lueg2f button:where(.svelte-lueg2f) {width:100%;}\n  }"
};
function fi(e, t) {
	qe(t, !1), Mr(e, di);
	let n = Kr(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!0), c = /* @__PURE__ */ N(!1), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = null, f = null, p = /* @__PURE__ */ N(!1), m = /* @__PURE__ */ N(!1), h = /* @__PURE__ */ N(!1);
	kr(async () => {
		n(n().replace(/\/$/, "")), await _(), P(s, !1);
	});
	async function g() {
		try {
			if (P(h, !0), !(await fetch(`${n()}/activate`, { method: "POST" })).ok) throw Error("Activation failed");
			await _();
		} catch (e) {
			console.error("Failed to activate server:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Activation failed. Check logs.",
				type: "error"
			} }));
		} finally {
			P(h, !1);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (P(r, e.settings.base_url || ""), P(i, e.settings.server_name || ""), P(a, e.settings.has_token || !1), P(o, e.settings.connected || !1), P(m, e.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e);
		}
	}
	async function ee() {
		if (!Z(r).trim()) {
			window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Server URL is required",
				type: "error"
			} }));
			return;
		}
		try {
			if (P(c, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					server_name: Z(i)
				})
			})).ok) throw Error("Save failed");
			await _(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Settings saved successfully",
				type: "success"
			} }));
		} catch (e) {
			console.error("Failed to save Plex settings:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Failed to save settings.",
				type: "error"
			} }));
		} finally {
			P(c, !1);
		}
	}
	async function te() {
		try {
			P(u, !0);
			let e = await (await fetch(`${n()}/auth/start`, { method: "POST" })).json();
			e?.oauth_url && e?.session_id && (d = e.session_id, window.open(e.oauth_url, "PlexOAuth", "width=600,height=700,menubar=no,status=no"), f = setInterval(async () => {
				try {
					(await (await fetch(`${n()}/auth/poll/${d}`)).json())?.completed && (clearInterval(f), f = null, P(u, !1), d = null, await _());
				} catch (e) {
					console.error("OAuth poll error:", e), e.status === 404 && (clearInterval(f), f = null, P(u, !1), d = null);
				}
			}, 3e3));
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e), P(u, !1);
		}
	}
	async function v() {
		if (d && f) {
			clearInterval(f), f = null;
			try {
				await fetch(`${n()}/auth/cancel/${d}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
			d = null, P(u, !1);
		}
	}
	async function ne() {
		try {
			P(l, !0), (await (await fetch(`${n()}/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Z(r) })
			})).json())?.connected ? (window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection successful!",
				type: "success"
			} })), await _()) : window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection failed. Check URL and ensure Plex is running.",
				type: "error"
			} }));
		} catch (e) {
			console.error("Connection test failed:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Test failed with error.",
				type: "error"
			} }));
		} finally {
			P(l, !1);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Lt();
		}
	};
	Wr();
	var b = ui(), x = I(b), S = I(x), re = L(I(S), 2), ie = I(re), ae = (e) => {
		$(e, $r());
	};
	jr(ie, (e) => {
		Z(m) && e(ae);
	});
	var oe = L(ie, 2), se = (e) => {
		$(e, ei());
	};
	jr(oe, (e) => {
		Z(a) && e(se);
	});
	var ce = L(oe, 2), le = (e) => {
		$(e, ti());
	}, ue = (e) => {
		$(e, ni());
	};
	jr(ce, (e) => {
		Z(o) ? e(le) : Z(a) && e(ue, 1);
	}), E(re), E(S);
	var de = L(S, 2), fe = I(de, !0);
	E(de), E(x);
	var pe = L(x, 2), me = (e) => {
		$(e, ri());
	}, he = (e) => {
		var t = li(), n = I(t), o = I(n), s = L(I(o), 2);
		Ir(s), Be(2), E(o);
		var d = L(o, 2), f = L(I(d), 2);
		Ir(f), E(d);
		var p = L(d, 2), _ = I(p), y = I(_, !0);
		E(_);
		var b = L(_, 2), x = (e) => {
			var t = ii(), n = I(t, !0);
			E(t), On((e) => {
				t.disabled = e, xr(n, Z(l) ? "Testing..." : "Test Connection");
			}, [() => (Z(l), Z(r), ar(() => Z(l) || !Z(r).trim()))]), fr("click", t, ne), $(e, t);
		};
		jr(b, (e) => {
			Z(a) && e(x);
		});
		var S = L(b, 2), re = (e) => {
			var t = ai(), n = I(t, !0);
			E(t), On(() => {
				t.disabled = Z(h), xr(n, Z(h) ? "Activating..." : "Activate for Sync");
			}), fr("click", t, g), $(e, t);
		};
		jr(S, (e) => {
			!Z(m) && Z(a) && e(re);
		});
		var ie = L(S, 2), ae = I(ie), oe = (e) => {
			var t = oi();
			fr("click", t, v), $(e, t);
		}, se = (e) => {
			var t = si();
			fr("click", t, te), $(e, t);
		}, ce = (e) => {
			var t = ci();
			fr("click", t, te), $(e, t);
		};
		jr(ae, (e) => {
			Z(u) ? e(oe) : Z(a) ? e(se, 1) : e(ce, -1);
		}), E(ie), E(p), E(n), E(t), On(() => {
			_.disabled = Z(c), xr(y, Z(c) ? "Saving..." : "Save Configuration");
		}), Vr(s, () => Z(r), (e) => P(r, e)), Vr(f, () => Z(i), (e) => P(i, e)), fr("click", _, ee), $(e, t);
	};
	return jr(pe, (e) => {
		Z(s) ? e(me) : Z(p) || e(he, 1);
	}), E(b), On(() => xr(fe, Z(p) ? "Expand" : "Collapse")), fr("click", de, () => P(p, !Z(p))), $(e, b), Je(y);
}
customElements.define("plex-dashboard-card", Qr(fi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { fi as default };
