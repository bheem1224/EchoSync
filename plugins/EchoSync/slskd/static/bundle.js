//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function ee(e) {
	return e();
}
function te(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function v() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var y = 1024, b = 2048, x = 4096, ne = 8192, re = 16384, ie = 32768, ae = 1 << 25, oe = 65536, se = 1 << 19, ce = 1 << 20, le = 65536, ue = 1 << 21, de = 1 << 22, fe = 1 << 23, pe = Symbol("$state"), me = Symbol("legacy props"), he = Symbol(""), ge = Symbol("attributes"), _e = Symbol("class"), ve = Symbol("style"), ye = Symbol("text"), be = Symbol("form reset"), xe = new class extends Error {
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
var S = !1;
function Re(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw Ie(), n;
	return C = e;
}
function ze() {
	return w(/* @__PURE__ */ F(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ F(C) !== null) throw Ie(), n;
		C = e;
	}
}
function Be(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ F(n);
		C = n;
	}
}
function Ve(e = !0) {
	for (var t = 0, n = C;;) {
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
	if (!e || e.nodeType !== 8) throw Ie(), n;
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
var E = null;
function Ke(e) {
	E = e;
}
function qe(t, n = !1, r) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: G,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) gn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, e ?? {};
}
function Ye() {
	return !e || E !== null && E.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], te(e);
}
function D(e) {
	if (Xe.length === 0 && !jt) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function Qe() {
	for (; Xe.length > 0;) Ze();
}
function $e(e) {
	var t = G;
	if (t === null) return H.f |= fe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	et(e, t);
}
function et(e, t) {
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
var tt = ~(b | x | y);
function O(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? O(e, y) : O(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= le, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), O(e, y);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1;
function ot(e) {
	var t = at;
	try {
		return at = !1, [e(), at];
	} finally {
		at = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var st = !1;
function ct() {
	st || (st = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[be]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function lt(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function ut(e, t, n, r = n) {
	e.addEventListener(t, () => lt(n));
	let i = e[be];
	e[be] = i ? () => {
		i(), r(!0);
	} : () => r(!0), ct();
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function dt(e) {
	let t = 0, n = qt(0), r;
	return () => {
		pn() && (Z(n), Sn(() => (t === 0 && (r = er(() => e(() => Xt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Xt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ft = oe | se;
function pt(e, t, n, r) {
	new mt(e, t, n, r);
}
var mt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = S ? C : null;
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
	#h = dt(() => (this.#m = qt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = wn(() => {
			if (S) {
				let e = this.#t;
				ze();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, ft), S && (this.#e = C);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		D(r), t && (this.#s = z(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				Le();
				return;
			}
			t = !0, n && Pe(), this.#s !== null && An(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					et(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = an();
			e.append(t), this.#a = this.#S(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, An(this.#o, () => {
				this.#o = null;
			}), this.#x(k));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Pn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#x(k);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = E;
		K(this.#i), W(this.#i), Ke(this.#i.ctx);
		try {
			return Lt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			K(t), W(n), Ke(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && An(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && Jt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), S && (w(this.#t), Be(), w(Ve()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return z(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return et(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				et(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => et(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function ht(e, t, n, r) {
	let i = Ye() ? yt : St;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = gt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				et(e, s);
			}
			_t();
		}
	}
	var d = vt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ xt(e))).then(u).catch((e) => et(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), _t();
	}) : f();
}
function gt() {
	var e = G, t = H, n = E, r = k;
	return function(i = !0) {
		K(e), W(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function _t(e = !0) {
	K(null), W(null), Ke(null), e && k?.deactivate();
}
function vt() {
	var e = G, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function yt(e) {
	var t = 2 | b;
	return G !== null && (G.f |= se), {
		ctx: E,
		deps: null,
		effects: null,
		equals: Ue,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: G,
		ac: null
	};
}
var bt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function xt(e, t, n) {
	let i = G;
	i === null && we();
	var a = void 0, o = qt(r), s = !H, c = /* @__PURE__ */ new Set();
	return xn(() => {
		var t = G, n = v();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== xe && n.reject(e);
			}).finally(_t);
		} catch (e) {
			n.reject(e), _t();
		}
		var r = k;
		if (s) {
			if (t.f & 32768) var l = vt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(bt);
			else for (let e of c.values()) e.reject(bt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== bt && (r.activate(), t ? (o.f |= fe, Jt(o, t)) : (o.f & 8388608 && (o.f ^= fe), Jt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), mn(() => {
		for (let e of c) e.reject(bt);
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
function St(e) {
	let t = /* @__PURE__ */ yt(e);
	return t.equals = Ge, t;
}
function Ct(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function wt(e) {
	var t, n = G, i = e.parent;
	if (!V && i !== null && e.v !== r && i.f & 24576) return Fe(), e.v;
	K(i);
	try {
		e.f &= ~le, Ct(e), t = qn(e);
	} finally {
		K(n);
	}
	return t;
}
function Tt(e) {
	var t = wt(e);
	if (!e.equals(t) && (e.wv = Wn(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), kt?.capture(e, t, !0)), e.deps === null))) {
		O(e, y);
		return;
	}
	V || (A === null ? nt(e) : (pn() || k?.is_fork) && A.set(e, t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && lt(() => {
		t.ac.abort(xe), t.ac = null;
	}), t.fn !== null && (t.teardown = _), Yn(t, 0), En(t));
}
function Dt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Xn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Ot = null, k = null, kt = null, A = null, At = null, jt = !1, Mt = !1, Nt = null, Pt = null, Ft = 0, It = 1, Lt = class e {
	id = It++;
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
		Ot === null ? Ot = this : (Ot.#n = this, this.#t = Ot), Ot = this;
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
		this.#e = !0, Ft++ > 1e3 && (this.#x(), zt());
		for (let e of this.#u) this.#d.delete(e), O(e, b), this.schedule(e);
		for (let e of this.#d) O(e, x), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Nt = [], r = [], i = Pt = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw Ut(e), this.#h() || this.discard(), t;
		}
		if (k = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Nt = null, Pt = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Ht(e, t);
			i.length > 0 && k.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), kt = this, Bt(r), Bt(n), kt = null, this.#s?.resolve();
		var s = k;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) {
			if (s !== null) {
				let e = s;
				e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
			} else s = this;
		}
		s !== null && s.#g();
	}
	#_(e, t, n) {
		e.f ^= y;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= y : i & 4 ? t.push(r) : Gn(r) && (i & 16 && this.#d.add(r), Xn(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
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
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), O(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), k = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), A?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		k = this;
	}
	deactivate() {
		k = null, A = null;
	}
	flush() {
		try {
			Mt = !0, k = this, this.#g();
		} finally {
			Ft = 0, At = null, Nt = null, Pt = null, Mt = !1, k = null, A = null, Gt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(bt);
		this.#x(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
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
		this.#m || (this.#m = !0, D(() => {
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
		return (this.#s ??= v()).promise;
	}
	static ensure() {
		if (k === null) {
			let t = k = new e();
			!Mt && !jt && D(() => {
				t.#e || t.flush();
			});
		}
		return k;
	}
	apply() {
		A = null;
	}
	schedule(e) {
		if (At = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Nt !== null && t === G && (H === null || !(H.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= y;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? Ot = e : t.#t = e, this.linked = !1;
		}
	}
};
function Rt(e) {
	var t = jt;
	jt = !0;
	try {
		var n;
		for (e && (k !== null && !k.is_fork && k.flush(), n = e());;) {
			if (Qe(), k === null) return n;
			k.flush();
		}
	} finally {
		jt = t;
	}
}
function zt() {
	try {
		Oe();
	} catch (e) {
		et(e, At);
	}
}
var j = null;
function Bt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Gn(r) && (j = /* @__PURE__ */ new Set(), Xn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && kn(r), j?.size > 0)) {
				Gt.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Xn(n);
					}
				}
				j.clear();
			}
		}
		j = null;
	}
}
function Vt(e) {
	k.schedule(e);
}
function Ht(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, y);
		for (var n = e.first; n !== null;) Ht(n, t), n = n.next;
	}
}
function Ut(e) {
	O(e, y);
	for (var t = e.first; t !== null;) Ut(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Wt = /* @__PURE__ */ new Set(), Gt = /* @__PURE__ */ new Map(), Kt = !1;
function qt(e, t) {
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
	let n = qt(e, t);
	return Rn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = qt(t);
	return n || (i.equals = Ge), e && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Ye() && H.f & 4325394 && (q === null || !q.has(e)) && Ne(), Jt(e, n ? Qt(t) : t, Pt);
}
function Jt(e, t, n = null) {
	if (!e.equals(t)) {
		Gt.set(e, V ? t : e.v);
		var r = Lt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && wt(t), A === null && nt(t);
		}
		e.wv = Wn(), Zt(e, b, n), Ye() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? zn([e]) : X.push(e)), !r.is_fork && Wt.size > 0 && !Kt && Yt();
	}
	return t;
}
function Yt() {
	Kt = !1;
	for (let e of Wt) {
		e.f & 1024 && O(e, x);
		let t;
		try {
			t = Gn(e);
		} catch {
			t = !0;
		}
		t && Xn(e);
	}
	Wt.clear();
}
function Xt(e) {
	P(e, e.v + 1);
}
function Zt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & b) === 0;
			if (l && O(s, t), c & 131072) Wt.add(s);
			else if (c & 2) {
				var u = s;
				A?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= le), Zt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && j !== null && j.add(d), n === null ? Vt(d) : n.push(d);
			}
		}
	}
}
function Qt(e) {
	if (typeof e != "object" || !e || pe in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ M(0), s = null, c = Hn, l = (e) => {
		if (Hn === c) return e();
		var t = H, n = Hn;
		W(null), Un(c);
		var r = e();
		return W(t), Un(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ M(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ M(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ M(r, s));
					n.set(t, e), Xt(o);
				}
			} else P(i, r), Xt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === pe) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ M(Qt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Z(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Z(a));
			} else if (i === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== r) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === pe) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || G !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ M(a ? Qt(e[t]) : r, s)), n.set(t, i)), Z(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ M(r, s)), n.set(p + "", m)) : P(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ M(void 0, s)), P(u, Qt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Qt(a));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && P(_, ee + 1);
				}
				Xt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Z(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			Me();
		}
	});
}
var $t, en, tn, nn;
function rn() {
	if ($t === void 0) {
		$t = window, en = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		tn = d(t, "firstChild").get, nn = d(t, "nextSibling").get, g(e) && (e[_e] = void 0, e[ge] = null, e[ve] = void 0, e.__e = void 0), g(n) && (n[ye] = void 0);
	}
}
function an(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function on(e) {
	return tn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function F(e) {
	return nn.call(e);
}
function I(e, t) {
	if (!S) return /* @__PURE__ */ on(e);
	var n = /* @__PURE__ */ on(C);
	if (n === null) n = C.appendChild(an());
	else if (t && n.nodeType !== 3) {
		var r = an();
		return n?.before(r), w(r), r;
	}
	return t && un(n), w(n), n;
}
function L(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ F(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = an();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		un(r);
	}
	return w(r), r;
}
function sn(e) {
	e.textContent = "";
}
function cn() {
	return !1;
}
function ln(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function un(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function dn(e) {
	G === null && (H === null && De(e), Ee()), V && Te(e);
}
function fn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ne);
	var r = {
		ctx: E,
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
	if (e & 4) Nt === null ? Lt.ensure().schedule(r) : Nt.push(r);
	else if (t !== null) {
		try {
			Xn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= oe));
	}
	if (i !== null && (i.parent = n, n !== null && fn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function pn() {
	return H !== null && !U;
}
function mn(e) {
	let t = R(8, null);
	return O(t, y), t.teardown = e, t;
}
function hn(e) {
	dn("$effect");
	var t = G.f;
	if (!H && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return gn(e);
}
function gn(e) {
	return R(4 | ce, e);
}
function _n(e) {
	return dn("$effect.pre"), R(8 | ce, e);
}
function vn(e) {
	Lt.ensure();
	let t = R(64 | se, e);
	return () => {
		B(t);
	};
}
function yn(e) {
	Lt.ensure();
	let t = R(64 | se, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? An(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function bn(e) {
	return R(4, e);
}
function xn(e) {
	return R(de | se, e);
}
function Sn(e, t = 0) {
	return R(8 | t, e);
}
function Cn(e, t = [], n = [], r = []) {
	ht(r, t, n, (t) => {
		R(8, () => {
			e(...t.map(Z));
		});
	});
}
function wn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | se, e);
}
function Tn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		Ln(!0), W(null);
		try {
			t.call(null);
		} finally {
			Ln(e), W(n);
		}
	}
}
function En(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && lt(() => {
			e.abort(xe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Dn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (On(e.nodes.start, e.nodes.end), n = !0), e.f |= ae, En(e, t && !n), Yn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Tn(e), e.f ^= ae, e.f |= re;
	var i = e.parent;
	i !== null && i.first !== null && kn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function On(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ F(e);
		e.remove(), e = n;
	}
}
function kn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function An(e, t, n = !0) {
	var r = [];
	jn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function jn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ne;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				jn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Mn(e) {
	Nn(e, !0);
}
function Nn(e, t) {
	if (e.f & 8192) {
		e.f ^= ne, e.f & 1024 || (O(e, b), Lt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Nn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Pn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ F(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Fn = null, In = !1, V = !1;
function Ln(e) {
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
function Rn(e) {
	H !== null && (q ??= /* @__PURE__ */ new Set()).add(e);
}
var J = null, Y = 0, X = null;
function zn(e) {
	X = e;
}
var Bn = 1, Vn = 0, Hn = Vn;
function Un(e) {
	Hn = e;
}
function Wn() {
	return ++Bn;
}
function Gn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~le), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Gn(a) && Tt(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, y);
	}
	return !1;
}
function Kn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(q !== null && q.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Kn(a, t, !1) : t === a && (n ? O(a, b) : a.f & 1024 && O(a, x), Vt(a));
	}
}
function qn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = E, s = U, c = Hn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ke(e.ctx), U = !1, Hn = ++Vn, e.ac !== null && (lt(() => {
		e.ac.abort(xe);
	}), e.ac = null);
	try {
		e.f |= ue;
		var u = e.fn, d = u();
		e.f |= ie;
		var f = e.deps, p = k?.is_fork;
		if (J !== null) {
			var m;
			if (p || Yn(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (pn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (Yn(e, Y), f.length = Y);
		if (Ye() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Kn(X[m], e);
		if (i !== null && i !== e) {
			if (Vn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Vn;
			if (t !== null) for (let e of t) e.rv = Vn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= fe), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= ue, J = t, Y = n, X = r, H = i, q = a, Ke(o), U = s, Hn = c;
	}
}
function Jn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !s.call(J, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~le), c.v !== r && nt(c), c.ac !== null && lt(() => {
			c.ac.abort(xe), c.ac = null, O(c, b);
		}), Et(c), Yn(c, 0);
	}
}
function Yn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Jn(e, n[r]);
}
function Xn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, y);
		var n = G, r = In;
		G = e, In = !(t & 96);
		try {
			t & 16777232 ? Dn(e) : En(e), Tn(e);
			var i = qn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Bn;
		} finally {
			In = r, G = n;
		}
	}
}
async function Zn() {
	await Promise.resolve(), Rt();
}
function Z(e) {
	var t = !!(e.f & 2);
	if (Fn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Vn && (e.rv = Vn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (V && Gt.has(e)) return Gt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || $n(i)) && (a = wt(i)), Gt.set(i, a), a;
		}
		var o = !(i.f & 512) && !U && H !== null && (In || !!(H.f & 512)), c = (i.f & ie) === 0;
		Gn(i) && (o && (i.f |= 512), Tt(i)), o && !c && (Dt(i), Qn(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Qn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Dt(t), Qn(t));
}
function $n(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Gt.has(t) || t.f & 2 && $n(t)) return !0;
	return !1;
}
function er(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function tr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (pe in e) nr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && pe in n && nr(n);
		}
	}
}
function nr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			nr(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
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
var rr = Symbol("events"), ir = /* @__PURE__ */ new Set(), ar = /* @__PURE__ */ new Set();
function or(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || lr.call(t, e), !e.cancelBubble) return lt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function sr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = or(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && mn(() => {
		t.removeEventListener(e, o, a);
	});
}
var cr = null;
function lr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	cr = e;
	var o = 0, s = cr === e && e[rr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[rr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[rr]?.[r];
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
			e[rr] = t, delete e.currentTarget, W(d), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var ur = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function dr(e) {
	return ur?.createHTML(e) ?? e;
}
function fr(e) {
	var t = ln("template");
	return t.innerHTML = dr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function pr(e, t) {
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
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (S) return pr(C, null), C;
		i === void 0 && (i = fr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ on(i)));
		var t = r || en ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ on(t), s = t.lastChild;
			pr(o, s);
		} else pr(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var mr = ["touchstart", "touchmove"];
function hr(e) {
	return mr.includes(e);
}
function gr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ye] ??= e.nodeValue) && (e[ye] = n, e.nodeValue = `${n}`);
}
function _r(e, t) {
	return br(e, t);
}
function vr(e, t) {
	rn(), t.intro = t.intro ?? !1;
	let r = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ on(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ F(o);
		if (!o) throw n;
		Re(!0), w(o);
		let i = br(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), rn(), sn(r), Re(!1), _r(e, t);
	} finally {
		Re(i), w(a);
	}
}
var yr = /* @__PURE__ */ new Map();
function br(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	rn();
	var u = void 0, d = yn(() => {
		var s = r ?? t.appendChild(an());
		pt(s, { pending: () => {} }, (t) => {
			qe({});
			var r = E;
			if (o && (r.c = o), a && (i.$$events = a), S && pr(t, null), u = e(t, i) || {}, S && (G.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Ie(), n;
			Je();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = hr(r);
					for (let e of [t, document]) {
						var a = yr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), yr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, lr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(ir)), ar.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = yr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, lr), n.delete(e), n.size === 0 && yr.delete(r)) : n.set(e, i);
			}
			ar.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return xr.set(u, d), u;
}
var xr = /* @__PURE__ */ new WeakMap();
function Sr(e, t) {
	let n = xr.get(e);
	return n ? (xr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Cr = class {
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
			if (n) Mn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Mn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						Pn(r, t), t.append(an()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), An(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = cn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = an();
				i.append(a), this.#n.set(e, {
					effect: z(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, z(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function wr(t) {
	E === null && Ce("onMount"), e && E.l !== null ? Tr(E).m.push(t) : hn(() => {
		let e = er(t);
		if (typeof e == "function") return e;
	});
}
function Tr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Er(e, t, n = !1) {
	var r;
	S && (r = C, ze());
	var i = new Cr(e), a = n ? oe : 0;
	function o(e, t) {
		if (S) {
			var n = He(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ve();
				w(a), i.anchor = a, Re(!1), i.ensure(e, t), Re(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	wn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Dr(e, t) {
	bn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = ln("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Or = Symbol("is custom element"), kr = Symbol("is html"), Ar = Se ? "link" : "LINK";
function jr(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Mr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Mr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[be] = n, D(n), ct();
	}
}
function Mr(e, t, n, r) {
	var i = Nr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Ar) || i[t] !== (i[t] = n) && (t === "loading" && (e[he] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Fr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Nr(e) {
	return e[ge] ??= {
		[Or]: e.nodeName.includes("-"),
		[kr]: e.namespaceURI === i
	};
}
var Pr = /* @__PURE__ */ new Map();
function Fr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Pr.get(t);
	if (n) return n;
	Pr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Ir(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ut(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Lr(e) ? Rr(a) : a, n(a), k !== null && r.add(k), await Zn(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && e.defaultValue !== e.value || er(t) == null && e.value) && (n(Lr(e) ? Rr(e.value) : e.value), k !== null && r.add(k)), Sn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = k;
			if (r.has(i)) return;
		}
		Lr(e) && n === Rr(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function Lr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Rr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function zr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => tr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ yt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && _n(() => {
		Br(t, r), te(n.b);
	}), hn(() => {
		let e = er(() => n.m.map(ee));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && hn(() => {
		Br(t, r), te(n.a);
	});
}
function Br(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Vr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ yt(i), Z(u)) : (l && (l = !1, c = s ? er(i) : i), c);
	let p;
	if (o) {
		var m = pe in t || me in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ot(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && Ae(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var ee = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || ee || g) && p(t ? _() : e), e) : _();
		});
	}
	var te = !1, v = (r & 1 ? yt : St)(() => (te = !1, _()));
	o && Z(v);
	var y = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(v) : a && o ? Qt(e) : e;
			return P(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return V && te || y.f & 16384 ? v.v : Z(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Hr(e) {
	return new Ur(e);
}
var Ur = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ N(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Z(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === me || (Z(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? vr : _r)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Rt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Sr(this.#t);
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
}, Wr;
typeof HTMLElement == "function" && (Wr = class extends HTMLElement {
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
					let n = ln("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Kr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Gr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Hr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = vn(() => {
				Sn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Gr(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Gr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Gr(e, t, n, r) {
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
function Kr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function qr(e, t, n, r, i, a) {
	let o = class extends Wr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Gr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SlskdCard.svelte
var Jr = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), Yr = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), Xr = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), Zr = /* @__PURE__ */ Q("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), Qr = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), $r = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), ei = /* @__PURE__ */ Q("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div>"), ti = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), ni = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}"
};
function ri(e, t) {
	qe(t, !1), Dr(e, ni);
	let n = Vr(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(""), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!0), c = /* @__PURE__ */ N(!1), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1), f = /* @__PURE__ */ N(!1), p = !1, m = /* @__PURE__ */ N(!1);
	wr(async () => {
		await _(), await h(), P(s, !1);
	});
	async function h() {
		try {
			let e = await (await fetch(`${n()}/providers/download-clients/active`)).json();
			P(m, e.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function g() {
		try {
			await fetch(`${n()}/providers/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), P(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/providers/soulseek/settings`)).json();
			e && (P(r, e.slskd_url || ""), P(a, e.server_name || ""), P(i, e.api_key || ""), P(f, e.has_api_key || !1), P(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function ee() {
		if (!Z(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			P(c, !0);
			let e = {
				slskd_url: Z(r),
				server_name: Z(a)
			};
			Z(i) && Z(i) !== "****" && (e.api_key = Z(i)), await fetch(`${n()}/providers/soulseek/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await _();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			P(c, !1);
		}
	}
	async function te() {
		if (Z(r).trim()) try {
			P(l, !0), (await (await fetch(`${n()}/providers/soulseek/connection/test`, { method: "POST" })).json())?.success ? (P(o, !0), await _()) : P(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), P(o, !1);
		} finally {
			P(l, !1);
		}
	}
	async function v() {
		let e = !Z(d);
		if (P(d, e), e && Z(f) && Z(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/providers/soulseek/settings/key`)).json();
			e && e.api_key ? (P(i, e.api_key), p = !0) : P(d, !1);
		} catch {
			P(d, !1);
		}
		!e && p && (P(i, "****"), p = !1);
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Rt();
		}
	};
	zr();
	var b = ti(), x = I(b), ne = I(x), re = L(I(ne), 2), ie = L(I(re), 2), ae = (e) => {
		$(e, Jr());
	}, oe = (e) => {
		$(e, Yr());
	};
	Er(ie, (e) => {
		Z(o) ? e(ae) : Z(r) && e(oe, 1);
	});
	var se = L(ie, 2), ce = (e) => {
		$(e, Xr());
	};
	Er(se, (e) => {
		Z(m) && e(ce);
	}), T(re), T(ne);
	var le = L(ne, 2), ue = I(le), de = (e) => {
		var t = Zr();
		sr("click", t, g), $(e, t);
	};
	Er(ue, (e) => {
		!Z(m) && Z(o) && e(de);
	});
	var fe = L(ue, 2), pe = I(fe, !0);
	T(fe), T(le), T(x);
	var me = L(x, 2), he = (e) => {
		$(e, Qr());
	}, ge = (e) => {
		var t = ei(), n = L(I(t), 2), o = I(n), s = L(I(o), 2);
		jr(s), Be(2), T(o);
		var u = L(o, 2), p = L(I(u), 2);
		jr(p), T(u);
		var m = L(u, 2), h = L(I(m), 2), g = I(h);
		jr(g);
		var _ = L(g, 2), y = I(_, !0);
		T(_), T(h), Be(2), T(m);
		var b = L(m, 2), x = I(b), ne = I(x, !0);
		T(x);
		var re = L(x, 2), ie = (e) => {
			var t = $r(), n = I(t, !0);
			T(t), Cn(() => {
				t.disabled = Z(l), gr(n, Z(l) ? "Testing..." : "Test Connection");
			}), sr("click", t, te), $(e, t);
		};
		Er(re, (e) => {
			Z(r) && (Z(f) || Z(i)) && e(ie);
		}), T(b), T(n), T(t), Cn(() => {
			Mr(g, "type", Z(d) ? "text" : "password"), gr(y, Z(d) ? "🙈" : "👁️"), x.disabled = Z(c), gr(ne, Z(c) ? "Saving..." : "Save Settings");
		}), Ir(s, () => Z(r), (e) => P(r, e)), Ir(p, () => Z(a), (e) => P(a, e)), Ir(g, () => Z(i), (e) => P(i, e)), sr("click", _, v), sr("click", x, ee), $(e, t);
	};
	return Er(me, (e) => {
		Z(s) ? e(he) : Z(u) || e(ge, 1);
	}), T(b), Cn(() => gr(pe, Z(u) ? "Expand" : "Collapse")), sr("click", fe, () => P(u, !Z(u))), $(e, b), Je(y);
}
customElements.define("slskd-dashboard-card", qr(ri, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ri as default };
