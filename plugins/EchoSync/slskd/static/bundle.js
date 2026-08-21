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
	return w(/* @__PURE__ */ I(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ I(C) !== null) throw Ie(), n;
		C = e;
	}
}
function Be(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ I(n);
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
		var i = /* @__PURE__ */ I(n);
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
		r: K,
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
		for (var r of n) hn(r);
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
	var t = K;
	if (t === null) return U.f |= fe, e;
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
	var t = U, n = K;
	G(null), q(null);
	try {
		return e();
	} finally {
		G(t), q(n);
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
	let t = 0, n = Kt(0), r;
	return () => {
		fn() && (Q(n), xn(() => (t === 0 && (r = $n(() => e(() => Yt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Yt(n));
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
	#h = dt(() => (this.#m = Kt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Cn(() => {
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
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		D(r), t && (this.#s = B(() => {
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
			t = !0, n && Pe(), this.#s !== null && kn(this.#s, () => {
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
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = rn();
			e.append(t), this.#a = this.#S(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, kn(this.#o, () => {
				this.#o = null;
			}), this.#x(k));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Nn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
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
		var t = K, n = U, r = E;
		q(this.#i), G(this.#i), Ke(this.#i.ctx);
		try {
			return Lt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			q(t), G(n), Ke(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && kn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && qt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Q(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), S && (w(this.#t), Be(), w(Ve()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return B(() => {
						var r = K;
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
	var s = K, c = gt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
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
	var e = K, t = U, n = E, r = k;
	return function(i = !0) {
		q(e), G(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function _t(e = !0) {
	q(null), G(null), Ke(null), e && k?.deactivate();
}
function vt() {
	var e = K, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function yt(e) {
	var t = 2 | b;
	return K !== null && (K.f |= se), {
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
		parent: K,
		ac: null
	};
}
var bt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function xt(e, t, n) {
	let i = K;
	i === null && we();
	var a = void 0, o = Kt(r), s = !U, c = /* @__PURE__ */ new Set();
	return bn(() => {
		var t = K, n = v();
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
			l?.(), c.delete(n), t !== bt && (r.activate(), t ? (o.f |= fe, qt(o, t)) : (o.f & 8388608 && (o.f ^= fe), qt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), pn(() => {
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
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function wt(e) {
	var t, n = K, i = e.parent;
	if (!H && i !== null && e.v !== r && i.f & 24576) return Fe(), e.v;
	q(i);
	try {
		e.f &= ~le, Ct(e), t = Kn(e);
	} finally {
		q(n);
	}
	return t;
}
function Tt(e) {
	var t = wt(e);
	if (!e.equals(t) && (e.wv = Un(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), kt?.capture(e, t, !0)), e.deps === null))) {
		O(e, y);
		return;
	}
	H || (A === null ? nt(e) : (fn() || k?.is_fork) && A.set(e, t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && lt(() => {
		t.ac.abort(xe), t.ac = null;
	}), t.fn !== null && (t.teardown = _), Jn(t, 0), Tn(t));
}
function Dt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Yn(t);
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
		s !== null && (M.clear(), s.#g());
	}
	#_(e, t, n) {
		e.f ^= y;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= y : i & 4 ? t.push(r) : Wn(r) && (i & 16 && this.#d.add(r), Yn(r));
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
			Ft = 0, At = null, Nt = null, Pt = null, Mt = !1, k = null, A = null, M.clear();
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
			if (Nt !== null && t === K && (U === null || !(U.f & 2))) return;
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
			if (!(r.f & 24576) && Wn(r) && (j = /* @__PURE__ */ new Set(), Yn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && On(r), j?.size > 0)) {
				M.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Yn(n);
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
var Wt = /* @__PURE__ */ new Set(), M = /* @__PURE__ */ new Map(), Gt = !1;
function Kt(e, t) {
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
function N(e, t) {
	let n = Kt(e, t);
	return Ln(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(t, n = !1, r = !0) {
	let i = Kt(t);
	return n || (i.equals = Ge), e && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && Ye() && U.f & 4325394 && (J === null || !J.has(e)) && Ne(), qt(e, n ? Zt(t) : t, Pt);
}
function qt(e, t, n = null) {
	if (!e.equals(t)) {
		H ? M.set(e, t) : M.has(e) || M.set(e, e.v);
		var r = Lt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && wt(t), A === null && nt(t);
		}
		e.wv = Un(), Xt(e, b, n), Ye() && K !== null && K.f & 1024 && !(K.f & 96) && (Z === null ? Rn([e]) : Z.push(e)), !r.is_fork && Wt.size > 0 && !Gt && Jt();
	}
	return t;
}
function Jt() {
	Gt = !1;
	for (let e of Wt) {
		e.f & 1024 && O(e, x);
		let t;
		try {
			t = Wn(e);
		} catch {
			t = !0;
		}
		t && Yn(e);
	}
	Wt.clear();
}
function Yt(e) {
	F(e, e.v + 1);
}
function Xt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === K)) {
			var l = (c & b) === 0;
			if (l && O(s, t), c & 131072) Wt.add(s);
			else if (c & 2) {
				var u = s;
				A?.delete(u), c & 65536 || (c & 512 && (K === null || !(K.f & 2097152)) && (s.f |= le), Xt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && j !== null && j.add(d), n === null ? Vt(d) : n.push(d);
			}
		}
	}
}
function Zt(e) {
	if (typeof e != "object" || !e || pe in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ N(0), s = null, c = Vn, l = (e) => {
		if (Vn === c) return e();
		var t = U, n = Vn;
		G(null), Hn(c);
		var r = e();
		return G(t), Hn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ N(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ N(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ N(r, s));
					n.set(t, e), Yt(o);
				}
			} else F(i, r), Yt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === pe) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ N(Zt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Q(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Q(a));
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
			return (i !== void 0 || K !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ N(a ? Zt(e[t]) : r, s)), n.set(t, i)), Q(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ N(r, s)), n.set(p + "", m)) : F(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ N(void 0, s)), F(u, Zt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Zt(a));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && F(_, ee + 1);
				}
				Yt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Q(o);
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
var Qt, $t, en, tn;
function nn() {
	if (Qt === void 0) {
		Qt = window, $t = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		en = d(t, "firstChild").get, tn = d(t, "nextSibling").get, g(e) && (e[_e] = void 0, e[ge] = null, e[ve] = void 0, e.__e = void 0), g(n) && (n[ye] = void 0);
	}
}
function rn(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function an(e) {
	return en.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function I(e) {
	return tn.call(e);
}
function L(e, t) {
	if (!S) return /* @__PURE__ */ an(e);
	var n = /* @__PURE__ */ an(C);
	if (n === null) n = C.appendChild(rn());
	else if (t && n.nodeType !== 3) {
		var r = rn();
		return n?.before(r), w(r), r;
	}
	return t && ln(n), w(n), n;
}
function R(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ I(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = rn();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		ln(r);
	}
	return w(r), r;
}
function on(e) {
	e.textContent = "";
}
function sn() {
	return !1;
}
function cn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function ln(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function un(e) {
	K === null && (U === null && De(e), Ee()), H && Te(e);
}
function dn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = K;
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
			Yn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= oe));
	}
	if (i !== null && (i.parent = n, n !== null && dn(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function fn() {
	return U !== null && !W;
}
function pn(e) {
	let t = z(8, null);
	return O(t, y), t.teardown = e, t;
}
function mn(e) {
	un("$effect");
	var t = K.f;
	if (!U && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return hn(e);
}
function hn(e) {
	return z(4 | ce, e);
}
function gn(e) {
	return un("$effect.pre"), z(8 | ce, e);
}
function _n(e) {
	Lt.ensure();
	let t = z(64 | se, e);
	return () => {
		V(t);
	};
}
function vn(e) {
	Lt.ensure();
	let t = z(64 | se, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? kn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function yn(e) {
	return z(4, e);
}
function bn(e) {
	return z(de | se, e);
}
function xn(e, t = 0) {
	return z(8 | t, e);
}
function Sn(e, t = [], n = [], r = []) {
	ht(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(Q));
		});
	});
}
function Cn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | se, e);
}
function wn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = H, n = U;
		In(!0), G(null);
		try {
			t.call(null);
		} finally {
			In(e), G(n);
		}
	}
}
function Tn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && lt(() => {
			e.abort(xe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function En(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Dn(e.nodes.start, e.nodes.end), n = !0), e.f |= ae, Tn(e, t && !n), Jn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	wn(e), e.f ^= ae, e.f |= re;
	var i = e.parent;
	i !== null && i.first !== null && On(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Dn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ I(e);
		e.remove(), e = n;
	}
}
function On(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function kn(e, t, n = !0) {
	var r = [];
	An(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function An(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ne;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				An(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function jn(e) {
	Mn(e, !0);
}
function Mn(e, t) {
	if (e.f & 8192) {
		e.f ^= ne, e.f & 1024 || (O(e, b), Lt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Mn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Nn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ I(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Pn = null, Fn = !1, H = !1;
function In(e) {
	H = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function q(e) {
	K = e;
}
var J = null;
function Ln(e) {
	U !== null && (J ??= /* @__PURE__ */ new Set()).add(e);
}
var Y = null, X = 0, Z = null;
function Rn(e) {
	Z = e;
}
var zn = 1, Bn = 0, Vn = Bn;
function Hn(e) {
	Vn = e;
}
function Un() {
	return ++zn;
}
function Wn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~le), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Wn(a) && Tt(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, y);
	}
	return !1;
}
function Gn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(J !== null && J.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Gn(a, t, !1) : t === a && (n ? O(a, b) : a.f & 1024 && O(a, x), Vt(a));
	}
}
function Kn(e) {
	var t = Y, n = X, r = Z, i = U, a = J, o = E, s = W, c = Vn, l = e.f;
	Y = null, X = 0, Z = null, U = l & 96 ? null : e, J = null, Ke(e.ctx), W = !1, Vn = ++Bn, e.ac !== null && (lt(() => {
		e.ac.abort(xe);
	}), e.ac = null);
	try {
		e.f |= ue;
		var u = e.fn, d = u();
		e.f |= ie;
		var f = e.deps, p = k?.is_fork;
		if (Y !== null) {
			var m;
			if (p || Jn(e, X), f !== null && X > 0) for (f.length = X + Y.length, m = 0; m < Y.length; m++) f[X + m] = Y[m];
			else e.deps = f = Y;
			if (fn() && e.f & 512) for (m = X; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && X < f.length && (Jn(e, X), f.length = X);
		if (Ye() && Z !== null && !W && f !== null && !(e.f & 6146)) for (m = 0; m < Z.length; m++) Gn(Z[m], e);
		if (i !== null && i !== e) {
			if (Bn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Bn;
			if (t !== null) for (let e of t) e.rv = Bn;
			Z !== null && (r === null ? r = Z : r.push(...Z));
		}
		return e.f & 8388608 && (e.f ^= fe), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= ue, Y = t, X = n, Z = r, U = i, J = a, Ke(o), W = s, Vn = c;
	}
}
function qn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (Y === null || !s.call(Y, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~le), c.v !== r && nt(c), c.ac !== null && lt(() => {
			c.ac.abort(xe), c.ac = null, O(c, b);
		}), Et(c), Jn(c, 0);
	}
}
function Jn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) qn(e, n[r]);
}
function Yn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, y);
		var n = K, r = Fn;
		K = e, Fn = !(t & 96);
		try {
			t & 16777232 ? En(e) : Tn(e), wn(e);
			var i = Kn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = zn;
		} finally {
			Fn = r, K = n;
		}
	}
}
async function Xn() {
	await Promise.resolve(), Rt();
}
function Q(e) {
	var t = !!(e.f & 2);
	if (Pn?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (J === null || !J.has(e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Bn && (e.rv = Bn, Y === null && n !== null && n[X] === e ? X++ : Y === null ? Y = [e] : Y.push(e));
		else {
			U.deps ??= [], s.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : s.call(r, U) || r.push(U);
		}
	}
	if (H && M.has(e)) return M.get(e);
	if (t) {
		var i = e;
		if (H) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Qn(i)) && (a = wt(i)), M.set(i, a), a;
		}
		var o = !(i.f & 512) && !W && U !== null && (Fn || !!(U.f & 512)), c = (i.f & ie) === 0;
		Wn(i) && (o && (i.f |= 512), Tt(i)), o && !c && (Dt(i), Zn(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Zn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Dt(t), Zn(t));
}
function Qn(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (M.has(t) || t.f & 2 && Qn(t)) return !0;
	return !1;
}
function $n(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function er(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (pe in e) tr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && pe in n && tr(n);
		}
	}
}
function tr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			tr(e[n], t);
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
var nr = Symbol("events"), rr = /* @__PURE__ */ new Set(), ir = /* @__PURE__ */ new Set();
function ar(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || lr.call(t, e), !e.cancelBubble) return lt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function or(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = ar(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && pn(() => {
		t.removeEventListener(e, o, a);
	});
}
var sr = null, cr = !1;
function lr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	sr = e, cr || (cr = !0, setTimeout(() => {
		cr = !1, sr = null;
	}));
	var o = 0, s = sr === e && e[nr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[nr] = t;
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
		var d = U, f = K;
		G(null), q(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[nr]?.[r];
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
			e[nr] = t, delete e.currentTarget, G(d), q(f);
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
	var t = cn("template");
	return t.innerHTML = dr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function pr(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function mr(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (S) return pr(C, null), C;
		i === void 0 && (i = fr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ an(i)));
		var t = r || $t ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ an(t), s = t.lastChild;
			pr(o, s);
		} else pr(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var hr = ["touchstart", "touchmove"];
function gr(e) {
	return hr.includes(e);
}
function _r(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ye] ??= e.nodeValue) && (e[ye] = n, e.nodeValue = `${n}`);
}
function vr(e, t) {
	return xr(e, t);
}
function yr(e, t) {
	nn(), t.intro = t.intro ?? !1;
	let r = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ an(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ I(o);
		if (!o) throw n;
		Re(!0), w(o);
		let i = xr(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), nn(), on(r), Re(!1), vr(e, t);
	} finally {
		Re(i), w(a);
	}
}
var br = /* @__PURE__ */ new Map();
function xr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	nn();
	var u = void 0, d = vn(() => {
		var s = r ?? t.appendChild(rn());
		pt(s, { pending: () => {} }, (t) => {
			qe({});
			var r = E;
			if (o && (r.c = o), a && (i.$$events = a), S && pr(t, null), u = e(t, i) || {}, S && (K.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Ie(), n;
			Je();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = gr(r);
					for (let e of [t, document]) {
						var a = br.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), br.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, lr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(rr)), ir.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = br.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, lr), n.delete(e), n.size === 0 && br.delete(r)) : n.set(e, i);
			}
			ir.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Sr.set(u, d), u;
}
var Sr = /* @__PURE__ */ new WeakMap();
function Cr(e, t) {
	let n = Sr.get(e);
	return n ? (Sr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var wr = class {
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
			if (n) jn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (jn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Nn(r, t), t.append(rn()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), kn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = sn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = rn();
				i.append(a), this.#n.set(e, {
					effect: B(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, B(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function Tr(t) {
	E === null && Ce("onMount"), e && E.l !== null ? Er(E).m.push(t) : mn(() => {
		let e = $n(t);
		if (typeof e == "function") return e;
	});
}
function Er(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Dr(e, t, n = !1) {
	var r;
	S && (r = C, ze());
	var i = new wr(e), a = n ? oe : 0;
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
	Cn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Or(e, t) {
	yn(() => {
		e = K?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = cn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var kr = Symbol("is custom element"), Ar = Symbol("is html"), jr = Se ? "link" : "LINK";
function Mr(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Nr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Nr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[be] = n, D(n), ct();
	}
}
function Nr(e, t, n, r) {
	var i = Pr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === jr) || i[t] !== (i[t] = n) && (t === "loading" && (e[he] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Ir(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Pr(e) {
	return e[ge] ??= {
		[kr]: e.nodeName.includes("-"),
		[Ar]: e.namespaceURI === i
	};
}
var Fr = /* @__PURE__ */ new Map();
function Ir(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Fr.get(t);
	if (n) return n;
	Fr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Lr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ut(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Rr(e) ? zr(a) : a, n(a), k !== null && r.add(k), await Xn(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && e.defaultValue !== e.value || $n(t) == null && e.value) && (n(Rr(e) ? zr(e.value) : e.value), k !== null && r.add(k)), xn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = k;
			if (r.has(i)) return;
		}
		Rr(e) && n === zr(e.value) || e.type === "date" && !n && !e.value || n !== e.value && (e.value = n ?? "");
	});
}
function Rr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function zr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Br(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => er(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ yt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Q(i);
	}
	n.b.length && gn(() => {
		Vr(t, r), te(n.b);
	}), mn(() => {
		let e = $n(() => n.m.map(ee));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && mn(() => {
		Vr(t, r), te(n.a);
	});
}
function Vr(e, t) {
	if (e.l.s) for (let t of e.l.s) Q(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Hr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ yt(i), Q(u)) : (l && (l = !1, c = s ? $n(i) : i), c);
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
	o && Q(v);
	var y = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Q(v) : a && o ? Zt(e) : e;
			return F(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return H && te || y.f & 16384 ? v.v : Q(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Ur(e) {
	return new Wr(e);
}
var Wr = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ P(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Q(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === me || (Q(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return F(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? yr : vr)(e.component, {
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
			Cr(this.#t);
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
}, Gr;
typeof HTMLElement == "function" && (Gr = class extends HTMLElement {
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
					let n = cn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = qr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Kr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Ur({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = _n(() => {
				xn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Kr(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Kr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function Kr(e, t, n, r) {
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
function qr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Jr(e, t, n, r, i, a) {
	let o = class extends Gr {
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
				n = Kr(e, n, t), this.$$d[e] = n;
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
var Yr = /* @__PURE__ */ mr("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), Xr = /* @__PURE__ */ mr("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), Zr = /* @__PURE__ */ mr("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), Qr = /* @__PURE__ */ mr("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), $r = /* @__PURE__ */ mr("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), ei = /* @__PURE__ */ mr("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), ti = /* @__PURE__ */ mr("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div>"), ni = /* @__PURE__ */ mr("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), ri = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}"
};
function ii(e, t) {
	qe(t, !1), Or(e, ri);
	let n = Hr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!0), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = !1, m = /* @__PURE__ */ P(!1);
	Tr(async () => {
		await _(), await h(), F(s, !1);
	});
	async function h() {
		try {
			let e = await (await fetch(`${n()}/download-clients/active`)).json();
			F(m, e.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function g() {
		try {
			await fetch(`${n()}/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), F(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e && (F(r, e.slskd_url || ""), F(a, e.server_name || ""), F(i, e.api_key || ""), F(f, e.has_api_key || !1), F(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function ee() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			F(c, !0);
			let e = {
				slskd_url: Q(r),
				server_name: Q(a)
			};
			Q(i) && Q(i) !== "****" && (e.api_key = Q(i)), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await _();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			F(c, !1);
		}
	}
	async function te() {
		if (Q(r).trim()) try {
			F(l, !0), (await (await fetch(`${n()}/connection/test`, { method: "POST" })).json())?.success ? (F(o, !0), await _()) : F(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), F(o, !1);
		} finally {
			F(l, !1);
		}
	}
	async function v() {
		let e = !Q(d);
		if (F(d, e), e && Q(f) && Q(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/settings/key`)).json();
			e && e.api_key ? (F(i, e.api_key), p = !0) : F(d, !1);
		} catch {
			F(d, !1);
		}
		!e && p && (F(i, "****"), p = !1);
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Rt();
		}
	};
	Br();
	var b = ni(), x = L(b), ne = L(x), re = R(L(ne), 2), ie = R(L(re), 2), ae = (e) => {
		$(e, Yr());
	}, oe = (e) => {
		$(e, Xr());
	};
	Dr(ie, (e) => {
		Q(o) ? e(ae) : Q(r) && e(oe, 1);
	});
	var se = R(ie, 2), ce = (e) => {
		$(e, Zr());
	};
	Dr(se, (e) => {
		Q(m) && e(ce);
	}), T(re), T(ne);
	var le = R(ne, 2), ue = L(le), de = (e) => {
		var t = Qr();
		or("click", t, g), $(e, t);
	};
	Dr(ue, (e) => {
		!Q(m) && Q(o) && e(de);
	});
	var fe = R(ue, 2), pe = L(fe, !0);
	T(fe), T(le), T(x);
	var me = R(x, 2), he = (e) => {
		$(e, $r());
	}, ge = (e) => {
		var t = ti(), n = R(L(t), 2), o = L(n), s = R(L(o), 2);
		Mr(s), Be(2), T(o);
		var u = R(o, 2), p = R(L(u), 2);
		Mr(p), T(u);
		var m = R(u, 2), h = R(L(m), 2), g = L(h);
		Mr(g);
		var _ = R(g, 2), y = L(_, !0);
		T(_), T(h), Be(2), T(m);
		var b = R(m, 2), x = L(b), ne = L(x, !0);
		T(x);
		var re = R(x, 2), ie = (e) => {
			var t = ei(), n = L(t, !0);
			T(t), Sn(() => {
				t.disabled = Q(l), _r(n, Q(l) ? "Testing..." : "Test Connection");
			}), or("click", t, te), $(e, t);
		};
		Dr(re, (e) => {
			Q(r) && (Q(f) || Q(i)) && e(ie);
		}), T(b), T(n), T(t), Sn(() => {
			Nr(g, "type", Q(d) ? "text" : "password"), _r(y, Q(d) ? "🙈" : "👁️"), x.disabled = Q(c), _r(ne, Q(c) ? "Saving..." : "Save Settings");
		}), Lr(s, () => Q(r), (e) => F(r, e)), Lr(p, () => Q(a), (e) => F(a, e)), Lr(g, () => Q(i), (e) => F(i, e)), or("click", _, v), or("click", x, ee), $(e, t);
	};
	return Dr(me, (e) => {
		Q(s) ? e(he) : Q(u) || e(ge, 1);
	}), T(b), Sn(() => _r(pe, Q(u) ? "Expand" : "Collapse")), or("click", fe, () => F(u, !Q(u))), $(e, b), Je(y);
}
customElements.define("slskd-dashboard-card", Jr(ii, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ii as default };
